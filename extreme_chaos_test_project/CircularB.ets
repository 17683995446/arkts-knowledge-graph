/**
 * 循环导入文件 B
 */

import { CircularC } from './CircularC';

export class CircularB {
    useC() {
        return new CircularC();
    }
}

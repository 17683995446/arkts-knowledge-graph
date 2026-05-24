/**
 * 循环导入链 3, 文件 0
 */

import { Class1 } from './CircularChain3_1';

export class Class0 {
    use1() {
        return new Class1();
    }
}

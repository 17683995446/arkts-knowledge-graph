/**
 * 循环链文件 3
 */

import { ChainClass4 } from './ChainFile4';

export class ChainClass3 {
    next() {
        return new ChainClass4();
    }
}

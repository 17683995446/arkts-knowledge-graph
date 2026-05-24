/**
 * 循环链文件 1
 */

import { ChainClass2 } from './ChainFile2';

export class ChainClass1 {
    next() {
        return new ChainClass2();
    }
}
